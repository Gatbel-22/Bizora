import { useCallback, useEffect, useRef, useState } from "react";

export default function useFetch(fetcher, key) {
  const fetcherRef = useRef(fetcher);
  const [reloadCount, setReloadCount] = useState(0);
  const [result, setResult] = useState({ requestKey: null, data: null, error: null });
  const requestKey = `${key}#${reloadCount}`;

  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    let active = true;
    fetcherRef
      .current()
      .then((data) => {
        if (active) setResult({ requestKey, data, error: null });
      })
      .catch((error) => {
        if (active) setResult((previous) => ({ requestKey, data: previous.data, error }));
      });
    return () => {
      active = false;
    };
  }, [requestKey]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);
  const settled = result.requestKey === requestKey;

  return {
    data: result.data,
    error: settled ? result.error : null,
    loading: !settled,
    reload,
  };
}
