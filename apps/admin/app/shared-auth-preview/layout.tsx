import Link from "next/link";

/** Legacy shared-auth page is source-locked; this additive link preserves RC3. */
export default function SharedAuthPreviewLayout({children}: Readonly<{children:React.ReactNode}>) {
  return <>
    {children}
    <nav aria-label="Работа ресепшен" style={{
      position: "fixed", bottom: 12, right: 12, zIndex: 30,
      background: "#fff", padding: "9px 15px", borderRadius: 9,
      boxShadow: "0 3px 12px rgba(0,0,0,.14)",
    }}>
      <Link href="/shared-reception">Ресепшен: создать бронь</Link>
    </nav>
  </>;
}
