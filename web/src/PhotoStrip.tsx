import type { Photo } from './projects'

export function PhotoStrip({ items }: { items: Photo[] }) {
  return <div className="photo-strip" aria-label="Project photos">
    {items.map((photo) => <figure key={photo.number} className="photo-tile">
      <img src={photo.src} alt={`Photo ${photo.number}`} />
      <figcaption>{photo.number}</figcaption>
    </figure>)}
  </div>
}
