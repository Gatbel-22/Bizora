from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.core.testing import make_member_client, make_owner
from apps.customers.models import CustomerPayment, Receivable

CUSTOMERS_URL = "/api/customers/"
RECEIVABLES_URL = "/api/receivables/"
PAYMENTS_URL = "/api/customer-payments/"


def days_from_today(days):
    return (timezone.localdate() + timedelta(days=days)).isoformat()


class CustomerTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")

    def create_customer(self, client=None, **overrides):
        payload = {"name": "Mama Rose", "phone": "+211911111111"}
        payload.update(overrides)
        response = (client or self.owner_a).post(CUSTOMERS_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def create_debt(self, customer, amount="1000.00", client=None, **overrides):
        payload = {"customer": customer["id"], "original_amount": amount}
        payload.update(overrides)
        response = (client or self.owner_a).post(RECEIVABLES_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def pay(self, customer, amount, client=None, **extra):
        payload = {"customer": customer["id"], "amount": amount, "method": "CASH"}
        payload.update(extra)
        return (client or self.owner_a).post(PAYMENTS_URL, payload, format="json")

    def balance_of(self, customer):
        response = self.owner_a.get(f"{CUSTOMERS_URL}{customer['id']}/")
        return Decimal(response.data["outstanding_balance"])

    def debts_by_note(self, **params):
        response = self.owner_a.get(RECEIVABLES_URL, params)
        self.assertEqual(response.status_code, 200)
        return {debt["note"]: debt for debt in response.data["results"]}


class CustomerTests(CustomerTestCase):
    def test_new_customer_owes_nothing(self):
        customer = self.create_customer()
        self.assertEqual(self.balance_of(customer), Decimal("0"))

    def test_name_is_required(self):
        response = self.owner_a.post(CUSTOMERS_URL, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data["error"]["details"])

    def test_search_by_name_and_phone(self):
        self.create_customer(name="Mama Rose", phone="0911")
        self.create_customer(name="John", phone="0922")
        by_name = self.owner_a.get(CUSTOMERS_URL, {"search": "rose"}).data["results"]
        by_phone = self.owner_a.get(CUSTOMERS_URL, {"search": "0922"}).data["results"]
        self.assertEqual([c["name"] for c in by_name], ["Mama Rose"])
        self.assertEqual([c["name"] for c in by_phone], ["John"])

    def test_staff_can_add_and_view_customers_but_not_edit_them(self):
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        customer = self.create_customer(client=staff, name="Walk-in Regular")
        self.assertEqual(staff.get(CUSTOMERS_URL).status_code, 200)
        response = staff.patch(f"{CUSTOMERS_URL}{customer['id']}/", {"name": "X"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_manager_can_edit_customers(self):
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        customer = self.create_customer()
        response = manager.patch(
            f"{CUSTOMERS_URL}{customer['id']}/", {"phone": "0999"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_customers_cannot_be_deleted(self):
        customer = self.create_customer()
        self.assertEqual(self.owner_a.delete(f"{CUSTOMERS_URL}{customer['id']}/").status_code, 405)

    def test_balance_filters(self):
        overdue = self.create_customer(name="Overdue")
        upcoming = self.create_customer(name="Upcoming")
        self.create_customer(name="Clear")
        self.create_debt(overdue, issue_date=days_from_today(-20), due_date=days_from_today(-1))
        self.create_debt(upcoming, due_date=days_from_today(10))

        def names(**params):
            response = self.owner_a.get(CUSTOMERS_URL, params)
            return sorted(c["name"] for c in response.data["results"])

        self.assertEqual(names(has_balance="true"), ["Overdue", "Upcoming"])
        self.assertEqual(names(overdue="true"), ["Overdue"])
        self.assertEqual(names(has_balance="false"), ["Clear"])


class ReceivableTests(CustomerTestCase):
    def test_new_debt_starts_unpaid(self):
        customer = self.create_customer()
        debt = self.create_debt(customer, amount="850000.00")
        self.assertEqual(Decimal(debt["balance"]), Decimal("850000"))
        self.assertEqual(Decimal(debt["amount_paid"]), Decimal("0"))
        self.assertEqual(debt["status"], "current")
        self.assertEqual(debt["days_outstanding"], 0)
        self.assertEqual(self.balance_of(customer), Decimal("850000"))

    def test_statuses_follow_the_due_date(self):
        customer = self.create_customer()
        self.create_debt(
            customer,
            note="late",
            issue_date=days_from_today(-20),
            due_date=days_from_today(-1),
        )
        self.create_debt(customer, note="soon", due_date=days_from_today(3))
        self.create_debt(customer, note="later", due_date=days_from_today(30))
        self.create_debt(customer, note="open-ended")
        settled = self.create_debt(customer, note="settled", amount="100.00")
        self.pay(customer, "100.00", receivable=settled["id"])

        statuses = {note: debt["status"] for note, debt in self.debts_by_note().items()}
        self.assertEqual(
            statuses,
            {
                "late": "overdue",
                "soon": "due_soon",
                "later": "current",
                "open-ended": "current",
                "settled": "paid",
            },
        )
        self.assertEqual(list(self.debts_by_note(status="overdue")), ["late"])
        self.assertEqual(list(self.debts_by_note(status="due_soon")), ["soon"])
        self.assertEqual(list(self.debts_by_note(status="paid")), ["settled"])
        self.assertEqual(len(self.debts_by_note(is_open="true")), 4)

    def test_days_outstanding_counts_from_the_issue_date(self):
        customer = self.create_customer()
        debt = self.create_debt(customer, issue_date=days_from_today(-10))
        self.assertEqual(debt["days_outstanding"], 10)

    def test_due_date_cannot_be_before_the_issue_date(self):
        customer = self.create_customer()
        response = self.owner_a.post(
            RECEIVABLES_URL,
            {
                "customer": customer["id"],
                "original_amount": "100.00",
                "issue_date": days_from_today(0),
                "due_date": days_from_today(-1),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("due_date", response.data["error"]["details"])

    def test_amount_must_be_positive(self):
        customer = self.create_customer()
        for amount in ("0", "-5"):
            response = self.owner_a.post(
                RECEIVABLES_URL,
                {"customer": customer["id"], "original_amount": amount},
                format="json",
            )
            self.assertEqual(response.status_code, 400, amount)

    def test_staff_can_view_debts_but_not_add_them(self):
        customer = self.create_customer()
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        self.assertEqual(staff.get(RECEIVABLES_URL).status_code, 200)
        response = staff.post(
            RECEIVABLES_URL,
            {"customer": customer["id"], "original_amount": "50.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_database_refuses_paying_more_than_was_owed(self):
        customer = self.create_customer()
        debt = self.create_debt(customer, amount="100.00")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Receivable.objects.filter(pk=debt["id"]).update(amount_paid=Decimal("150.00"))


class PaymentTests(CustomerTestCase):
    def test_partial_then_full_payment(self):
        customer = self.create_customer()
        debt = self.create_debt(customer, amount="1000.00", due_date=days_from_today(10))

        first = self.pay(customer, "400.00")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(self.balance_of(customer), Decimal("600"))
        self.assertEqual(Receivable.objects.get(pk=debt["id"]).amount_paid, Decimal("400"))

        second = self.pay(customer, "600.00", method="MOBILE_MONEY")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(self.balance_of(customer), Decimal("0"))
        paid = self.owner_a.get(f"{RECEIVABLES_URL}{debt['id']}/").data
        self.assertEqual(paid["status"], "paid")
        self.assertIsNone(paid["days_outstanding"])

    def test_payment_settles_the_oldest_due_debt_first(self):
        customer = self.create_customer()
        self.create_debt(customer, amount="500.00", note="later", due_date=days_from_today(5))
        self.create_debt(
            customer,
            amount="800.00",
            note="earlier",
            issue_date=days_from_today(-10),
            due_date=days_from_today(-2),
        )

        response = self.pay(customer, "900.00")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data["allocations"]), 2)

        debts = self.debts_by_note()
        self.assertEqual(debts["earlier"]["status"], "paid")
        self.assertEqual(Decimal(debts["later"]["balance"]), Decimal("400"))

    def test_payment_can_target_one_debt(self):
        customer = self.create_customer()
        self.create_debt(customer, amount="500.00", note="first", due_date=days_from_today(2))
        second = self.create_debt(
            customer, amount="300.00", note="second", due_date=days_from_today(9)
        )

        response = self.pay(customer, "100.00", receivable=second["id"])
        self.assertEqual(response.status_code, 201, response.data)
        debts = self.debts_by_note()
        self.assertEqual(Decimal(debts["first"]["balance"]), Decimal("500"))
        self.assertEqual(Decimal(debts["second"]["balance"]), Decimal("200"))

    def test_overpayment_is_refused_and_changes_nothing(self):
        customer = self.create_customer()
        self.create_debt(customer, amount="1000.00")
        response = self.pay(customer, "1500.00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount", response.data["error"]["details"])
        self.assertEqual(self.balance_of(customer), Decimal("1000"))
        self.assertEqual(CustomerPayment.objects.count(), 0)

    def test_paying_a_customer_who_owes_nothing_is_refused(self):
        customer = self.create_customer()
        response = self.pay(customer, "10.00")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CustomerPayment.objects.count(), 0)

    def test_invalid_amounts_and_methods_are_refused(self):
        customer = self.create_customer()
        self.create_debt(customer)
        for amount in ("0", "-10"):
            self.assertEqual(self.pay(customer, amount).status_code, 400, amount)
        response = self.pay(customer, "10.00", method="CREDIT")
        self.assertEqual(response.status_code, 400)
        self.assertIn("method", response.data["error"]["details"])

    def test_cannot_apply_a_payment_to_another_customers_debt(self):
        rose = self.create_customer(name="Rose")
        john = self.create_customer(name="John")
        john_debt = self.create_debt(john)
        self.create_debt(rose)
        response = self.pay(rose, "10.00", receivable=john_debt["id"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("receivable", response.data["error"]["details"])

    def test_staff_can_record_payments(self):
        customer = self.create_customer()
        self.create_debt(customer)
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        self.assertEqual(self.pay(customer, "100.00", client=staff).status_code, 201)

    def test_payment_history_can_be_filtered_by_customer(self):
        rose = self.create_customer(name="Rose")
        john = self.create_customer(name="John")
        self.create_debt(rose)
        self.create_debt(john)
        self.pay(rose, "10.00")
        self.pay(john, "20.00")
        response = self.owner_a.get(PAYMENTS_URL, {"customer": rose["id"]})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(Decimal(response.data["results"][0]["amount"]), Decimal("10"))

    def test_debts_and_payments_are_written_to_the_audit_log(self):
        customer = self.create_customer()
        self.create_debt(customer, amount="250.00")
        self.pay(customer, "50.00")
        actions = set(AuditLog.objects.values_list("action", flat=True))
        self.assertTrue({"customer.created", "receivable.created", "payment.recorded"} <= actions)


class CustomerTenantIsolationTests(CustomerTestCase):
    def setUp(self):
        super().setUp()
        self.customer = self.create_customer()
        self.debt = self.create_debt(self.customer, amount="1000.00")
        self.pay(self.customer, "100.00")

    def test_other_business_sees_nothing(self):
        for url in (CUSTOMERS_URL, RECEIVABLES_URL, PAYMENTS_URL):
            response = self.owner_b.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response.data["count"], 0, url)

    def test_other_business_cannot_open_or_edit_a_customer(self):
        url = f"{CUSTOMERS_URL}{self.customer['id']}/"
        self.assertEqual(self.owner_b.get(url).status_code, 404)
        self.assertEqual(self.owner_b.patch(url, {"name": "X"}, format="json").status_code, 404)

    def test_other_business_cannot_add_debts_or_payments_to_our_customer(self):
        response = self.owner_b.post(
            RECEIVABLES_URL,
            {"customer": self.customer["id"], "original_amount": "50.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("customer", response.data["error"]["details"])
        response = self.pay(self.customer, "50.00", client=self.owner_b)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.balance_of(self.customer), Decimal("900"))

    def test_other_business_cannot_target_our_debt(self):
        theirs = self.create_customer(client=self.owner_b, name="Their customer")
        self.create_debt(theirs, client=self.owner_b)
        response = self.pay(theirs, "10.00", client=self.owner_b, receivable=self.debt["id"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.balance_of(self.customer), Decimal("900"))
        self.assertIsNotNone(APIClient())
