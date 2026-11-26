export interface Photo {
  number: number
  src: string
}

export interface Project {
  id: string
  photos: Photo[]
  canvas: { width: number; height: number }
}

export const canvasPresets = [
  { value: '2:3', label: 'Portrait 2:3', width: 1200, height: 1800 },
  { value: '3:4', label: 'Portrait 3:4', width: 1200, height: 1600 },
  { value: '9:16', label: 'Portrait 9:16', width: 900, height: 1600 },
  { value: '1:1', label: 'Square 1:1', width: 1200, height: 1200 },
  { value: '3:2', label: 'Landscape 3:2', width: 1800, height: 1200 },
  { value: '4:3', label: 'Landscape 4:3', width: 1600, height: 1200 },
  { value: '16:9', label: 'Landscape 16:9', width: 1600, height: 900 },
]

export function projectIdError(id: string) {
  if (!/^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$/.test(id)) {
    return 'Use 1-64 lowercase letters, digits or hyphens, starting and ending with a letter or digit.'
  }
  if (/^(con|prn|aux|nul|(com|lpt)[1-9])$/.test(id)) {
    return 'Project ID cannot be a reserved Windows device name.'
  }
  return ''
}
