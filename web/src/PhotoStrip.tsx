import type { Photo } from './projects'
import { useState } from 'react'

function Thumbnail({ photo }: { photo: Photo }) {
  const [failed, setFailed] = useState(false)
  return <figure className="photo-tile">
      {failed ? <span role="alert">Photo {photo.number} could not load.</span>
        : <img src={photo.src} crossOrigin="anonymous" alt={`Photo ${photo.number}`} onError={() => setFailed(true)} />}
      <figcaption>{photo.number}</figcaption>
    </figure>
}

export function PhotoStrip({ items }: { items: Photo[] }) {
  return <div className="photo-strip" aria-label="Project photos">
    {items.map((photo) => <Thumbnail key={photo.src} photo={photo} />)}
  </div>
}
