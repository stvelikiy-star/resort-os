import { notFound } from "next/navigation";

export default function DemoPage() {
  // Historical client demo is intentionally disabled in the final management build.
  // The authenticated AdminShell is the only supported owner/manager surface.
  notFound();
}
