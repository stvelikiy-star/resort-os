"use client";

import { useEffect } from "react";

const MIXED_SCRIPT_FIXES: Array<[RegExp, string]> = [
  [/КОНok/g, "КОНОК"],
  [/Конok/g, "Конок"],
];

function sanitize(node: Node) {
  if (node.nodeType === Node.TEXT_NODE) {
    let value = node.nodeValue || "";
    for (const [pattern, replacement] of MIXED_SCRIPT_FIXES) value = value.replace(pattern, replacement);
    if (value !== node.nodeValue) node.nodeValue = value;
    return;
  }
  for (const child of Array.from(node.childNodes)) sanitize(child);
}

export default function AdminLocaleSanitizer() {
  useEffect(() => {
    sanitize(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") sanitize(mutation.target);
        for (const node of Array.from(mutation.addedNodes)) sanitize(node);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
