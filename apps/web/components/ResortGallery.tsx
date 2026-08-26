"use client";

import { useEffect, useRef, useState } from "react";

type GalleryImage = { src: string; alt: string; label: string; };

export default function ResortGallery({ images }: { images: GalleryImage[] }) {
  const [active, setActive] = useState<number | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (active === null) return;
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActive(null);
      if (event.key === "ArrowRight") setActive((current) => current === null ? null : (current + 1) % images.length);
      if (event.key === "ArrowLeft") setActive((current) => current === null ? null : (current - 1 + images.length) % images.length);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active, images.length]);

  return (
    <>
      <div className="gallery-grid wrap">{images.map((image, index) => <button className={`gallery-item gallery-item-${index + 1}`} type="button" key={image.src} onClick={() => setActive(index)} aria-label={`Открыть фотографию: ${image.label}`}><img src={image.src} alt={image.alt} loading={index < 2 ? "eager" : "lazy"} /><span>{image.label}</span></button>)}</div>
      {active !== null && <div className="lightbox" role="dialog" aria-modal="true" aria-label="Просмотр фотографии" onMouseDown={() => setActive(null)}><div className="lightbox-inner" onMouseDown={(event) => event.stopPropagation()}><button ref={closeButtonRef} className="lightbox-close" type="button" onClick={() => setActive(null)} aria-label="Закрыть">×</button><button className="lightbox-arrow prev" type="button" onClick={() => setActive((active - 1 + images.length) % images.length)} aria-label="Предыдущая фотография">←</button><img src={images[active].src} alt={images[active].alt} /><button className="lightbox-arrow next" type="button" onClick={() => setActive((active + 1) % images.length)} aria-label="Следующая фотография">→</button><p>{images[active].label} · {active + 1}/{images.length}</p></div></div>}
    </>
  );
}
