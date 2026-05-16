import { useEffect, useState } from "react";

/**
 * Decipher logo. Uses the brand assets the user supplied:
 *   /logo-light.png on light backgrounds
 *   /logo-dark.png on dark backgrounds
 * Alpha PNGs (background knocked out from the JPEG source), so they drop
 * cleanly onto the toolbar surface in either theme.
 *
 * Falls back to wordmark text if either image is missing.
 */
export function Logo({ height = 32 }: { height?: number }) {
  const [isDark, setIsDark] = useState(false);
  const [errLight, setErrLight] = useState(false);
  const [errDark, setErrDark] = useState(false);

  useEffect(() => {
    const compute = () => {
      const explicit = document.documentElement.getAttribute("data-theme");
      if (explicit === "dark")  return setIsDark(true);
      if (explicit === "light") return setIsDark(false);
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      setIsDark(mq.matches);
    };
    compute();
    const observer = new MutationObserver(compute);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener?.("change", compute);
    return () => { observer.disconnect(); mq.removeEventListener?.("change", compute); };
  }, []);

  const src = isDark ? "/logo-dark.png" : "/logo-light.png";
  const err = isDark ? errDark : errLight;

  if (err) {
    return (
      <span
        className="hig-headline"
        style={{ color: "var(--colour-label)", letterSpacing: "-0.01em", fontWeight: 700 }}
      >
        Decipher
      </span>
    );
  }

  return (
    <img
      src={src}
      alt="Decipher"
      height={height}
      onError={() => (isDark ? setErrDark(true) : setErrLight(true))}
      style={{
        height,
        width: "auto",
        maxWidth: 200,
        objectFit: "contain",
        display: "block",
      }}
    />
  );
}
