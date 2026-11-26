import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { conversation, transcript } from './test/conversation'

const canvas = { width: 2048, height: 1024 }
const detail = {
  project_id: 'sample-london', canvas,
  photos: [{ photo_id: 1, width: 40, height: 20 }, { photo_id: 2, width: 20, height: 40 }],
}
function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
}
function openSetup() {
  fireEvent.click(screen.getAllByRole('link', { name: 'New project' })[0])
}
function files() {
  return [
    new File(['first'], 'first.jpg', { type: 'image/jpeg' }),
    new File(['second'], 'second.png', { type: 'image/png' }),
  ]
}
async function fillSetup(id = 'sample-london') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Project ID'), id)
  await user.upload(screen.getByLabelText('Choose 2-6 photos'), files())
  fireEvent.load(screen.getByAltText('Selected photo 1'))
  fireEvent.load(screen.getByAltText('Selected photo 2'))
  fireEvent.change(screen.getByLabelText('Width (px)'), { target: { value: '2048' } })
  fireEvent.change(screen.getByLabelText('Height (px)'), { target: { value: '1024' } })
}

beforeEach(() => {
  history.replaceState(null, '', '/')
  let number = 0
  vi.spyOn(URL, 'createObjectURL').mockImplementation(() => `blob:local-${++number}`)
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
})

describe('saved project flow', () => {
  it('distinguishes loading, empty and failed lists without substituting sample projects', async () => {
    let resolve!: (value: Response) => void
    vi.mocked(fetch).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading projects')
    await act(async () => { resolve(json({ projects: [] })) })
    expect(screen.getByText('No saved projects yet.')).toBeVisible()
    expect(within(screen.getByRole('navigation')).getAllByRole('link').map((link) => link.textContent))
      .toEqual(['Projects', 'New project'])
    expect(screen.queryByRole('link', { name: /demo/i })).not.toBeInTheDocument()
    openSetup()
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('stopped'))
    fireEvent.click(screen.getByRole('link', { name: 'Projects' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach')
    expect(screen.queryByText('No saved projects yet.')).not.toBeInTheDocument()
    vi.mocked(fetch).mockResolvedValueOnce(json({ projects: [{ ...detail, photo_count: 2 }] }))
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('link', { name: 'sample-london' })).toHaveAttribute('href', '/projects/sample-london')
  })

  it('creates from selected files/custom pixels only after persistence and reopens via independent GETs', async () => {
    history.replaceState(null, '', '/new')
    let finish!: (value: Response) => void
    vi.mocked(fetch).mockImplementationOnce(() => new Promise((done) => { finish = done }))
      .mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(conversation({ project_id: 'sample-london' })))
      .mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(conversation({ project_id: 'sample-london' })))
    const view = render(<App />)
    expect(screen.getByText(/saved locally by the backend without model requests/)).toBeVisible()
    expect(screen.getByText(/enable live conversation to request a collage/)).toBeVisible()
    await fillSetup()
    fireEvent.click(screen.getByRole('button', { name: 'Create project' }))
    fireEvent.submit(document.querySelector('form')!)
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(location.pathname).toBe('/new')
    expect(screen.getByLabelText('Project ID')).toBeDisabled()
    const body = vi.mocked(fetch).mock.calls[0][1]?.body as FormData
    expect(JSON.parse(body.get('metadata') as string)).toEqual({ project_id: 'sample-london', canvas })
    expect(body.get('photo_1')).toBeInstanceOf(File)
    await act(async () => { finish(json(detail, 201)) })
    expect(await screen.findByRole('heading', { name: 'sample-london' })).toBeVisible()
    expect(screen.getByText(/2 photos.*2048 x 1024/)).toBeVisible()
    expect(screen.getByAltText('Photo 1')).toHaveAttribute('src',
      'http://127.0.0.1:7071/api/projects/sample-london/photos/1')
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
    await waitFor(() => expect(screen.getByLabelText('Your message')).toBeEnabled())
    expect(screen.queryByRole('button', { name: 'Accept proposal' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Download PNG' })).not.toBeInTheDocument()
    view.unmount()
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'sample-london' })).toBeVisible()
    expect(vi.mocked(fetch).mock.calls.map((call) => call[1]?.method)).toEqual(['POST', 'GET', 'GET', 'GET', 'GET'])
    expect(Storage.prototype.getItem).not.toHaveBeenCalled()
    expect(Storage.prototype.setItem).not.toHaveBeenCalled()
  })

  it.each([
    [409, { error: { code: 'project_exists', message: 'That ID exists.' } }],
    [500, { error: { code: 'storage_error', message: 'Storage failed.' } }],
    [0, null],
  ])('preserves failed submissions and explicitly looks up the submitted ID (%s)', async (status, error) => {
    history.replaceState(null, '', '/new')
    if (status) vi.mocked(fetch).mockResolvedValueOnce(json(error, status))
    else vi.mocked(fetch).mockRejectedValueOnce(new TypeError('lost response'))
    render(<App />)
    await fillSetup()
    fireEvent.click(screen.getByRole('button', { name: 'Create project' }))
    const lookup = await screen.findByRole('button', { name: 'Check saved project sample-london' })
    expect(location.pathname).toBe('/new')
    expect(screen.getByLabelText('Project ID')).toHaveValue('sample-london')
    expect(screen.getByLabelText('Width (px)')).toHaveValue(2048)
    expect(screen.getByAltText('Selected photo 1')).toHaveAttribute('src', 'blob:local-1')
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()
    if (status !== 409) expect(screen.getByRole('alert')).toHaveTextContent('may have been saved')
    fireEvent.change(screen.getByLabelText('Project ID'), { target: { value: 'another-id' } })
    vi.mocked(fetch).mockResolvedValueOnce(json(detail)).mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(conversation({ project_id: 'sample-london' })))
    fireEvent.click(lookup)
    expect(await screen.findByRole('heading', { name: 'sample-london' })).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it('shows missing/corrupt detail failures and photo-load errors without demo history', async () => {
    history.replaceState(null, '', '/projects/sample-london')
    vi.mocked(fetch).mockResolvedValueOnce(json({ error: { message: 'Not found.' } }, 404))
      .mockResolvedValueOnce(json({ error: { message: 'State is invalid.' } }, 409))
      .mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(conversation({ project_id: 'sample-london' })))
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Project not found' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('heading', { name: 'Could not load project' })).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('State is invalid')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    await screen.findByAltText('Photo 1')
    fireEvent.error(screen.getByAltText('Photo 1'))
    expect(screen.getByRole('alert')).toHaveTextContent('Photo 1')
    expect(screen.getByRole('log')).toBeInTheDocument()
  })

  it('aborts navigation-away requests and ignores responses that arrive afterward', async () => {
    history.replaceState(null, '', '/projects/old')
    let finish!: (value: Response) => void
    vi.mocked(fetch).mockImplementationOnce(() => new Promise((done) => { finish = done }))
    render(<App />)
    const signal = vi.mocked(fetch).mock.calls[0][1]?.signal
    openSetup()
    expect(signal?.aborted).toBe(true)
    await act(async () => { finish(json({ ...detail, project_id: 'old' })) })
    expect(screen.getByRole('heading', { name: 'New project' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'old' })).not.toBeInTheDocument()
  })

  it('keeps an explicit lookup after navigating away from an uncertain create', async () => {
    history.replaceState(null, '', '/new')
    vi.mocked(fetch).mockImplementationOnce(() => new Promise(() => {}))
      .mockResolvedValueOnce(json({ projects: [] })).mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(conversation({ project_id: 'sample-london' })))
    render(<App />)
    await fillSetup()
    fireEvent.click(screen.getByRole('button', { name: 'Create project' }))
    const signal = vi.mocked(fetch).mock.calls[0][1]?.signal
    fireEvent.click(screen.getByRole('link', { name: 'Cancel' }))
    expect(signal?.aborted).toBe(true)
    expect(screen.getByRole('alert')).toHaveTextContent('may have finished after you left')
    fireEvent.click(screen.getByRole('link', { name: 'Check saved project sample-london' }))
    expect(await screen.findByRole('heading', { name: 'sample-london' })).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
    expect(fetch).toHaveBeenCalledTimes(4)
  })

  it('validates files, IDs and canvas bounds before upload and releases previews', async () => {
    history.replaceState(null, '', '/new')
    const user = userEvent.setup({ applyAccept: false })
    const { unmount } = render(<App />)
    const input = screen.getByLabelText('Choose 2-6 photos')
    await user.upload(input, files()[0])
    expect(screen.getByRole('alert')).toHaveTextContent('between 2 and 6')
    await user.upload(input, [files()[0], new File(['bad'], 'bad.bmp', { type: 'image/bmp' })])
    expect(screen.getByRole('alert')).toHaveTextContent('JPEG or PNG')
    const large = files()[0]
    Object.defineProperty(large, 'size', { value: 25 * 1024 * 1024 + 1 })
    await user.upload(input, [large, files()[1]])
    expect(screen.getByRole('alert')).toHaveTextContent('25 MiB or smaller')
    await fillSetup('UPPER')
    const submit = screen.getByRole('button', { name: 'Create project' })
    fireEvent.click(submit)
    expect(screen.getByRole('alert')).toHaveTextContent('lowercase letters')
    fireEvent.change(screen.getByLabelText('Project ID'), { target: { value: 'con' } })
    fireEvent.click(submit)
    expect(screen.getByRole('alert')).toHaveTextContent('reserved Windows')
    fireEvent.change(screen.getByLabelText('Project ID'), { target: { value: 'valid' } })
    for (const value of ['0', '4097', '12.5', '']) {
      fireEvent.change(screen.getByLabelText('Width (px)'), { target: { value } })
      fireEvent.click(submit)
      expect(screen.getByRole('alert')).toHaveTextContent('whole pixels')
    }
    fireEvent.change(screen.getByLabelText('Width (px)'), { target: { value: '1' } })
    fireEvent.error(screen.getByAltText('Selected photo 1'))
    fireEvent.click(submit)
    expect(screen.getAllByRole('alert').some((item) => item.textContent?.includes('readable photos'))).toBe(true)
    expect(fetch).not.toHaveBeenCalled()
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
  })
})

describe('navigation without the scripted prototype', () => {
  it('treats the retired Demo URL as not found without loading a fake project or calling the API', () => {
    history.replaceState(null, '', '/demo')
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Back to projects' })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('log')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Demo' })).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('opens a real project from the list with its restored collage, photos and historical modal', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(json({ projects: [{ ...detail, photo_count: 2 }] }))
      .mockResolvedValueOnce(json(detail))
      .mockResolvedValueOnce(json(conversation({
        project_id: 'sample-london', baseline: { proposal_id: 'P002' }, messages: transcript(),
      })))
    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: 'sample-london' }))
    await screen.findByAltText('Proposal P002')
    expect(document.title).toBe('sample-london - Collage studio')
    expect(screen.getByText(/2 photos.*2048 x 1024/)).toBeVisible()
    expect(screen.getByAltText('Photo 1')).toHaveAttribute('src',
      'http://127.0.0.1:7071/api/projects/sample-london/photos/1')
    expect(screen.getByLabelText('Your message')).toBeEnabled()
    expect(within(screen.getByRole('region', { name: 'Current collage' }))
      .getByRole('button', { name: 'Download PNG' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'View collage P002' }))
    const modal = screen.getByRole('dialog', { name: 'Collage P002' })
    expect(within(modal).getByRole('button', { name: 'Already current' })).toBeDisabled()
    expect(within(modal).getByRole('button', { name: 'Download PNG' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: 'Accept proposal' })).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(vi.mocked(fetch).mock.calls.every(([, options]) => options?.method === 'GET')).toBe(true)
  })

  it('supports browser back and forward between a real saved workspace and setup', async () => {
    history.replaceState(null, '', '/projects/sample-london')
    const snapshot = conversation({ project_id: 'sample-london', baseline: { proposal_id: 'P002' } })
    vi.mocked(fetch).mockResolvedValueOnce(json(detail)).mockResolvedValueOnce(json(snapshot))
      .mockResolvedValueOnce(json(detail)).mockResolvedValueOnce(json(snapshot))
    render(<App />)
    await screen.findByAltText('Proposal P002')
    openSetup()
    act(() => history.back())
    await waitFor(() => expect(screen.getByRole('heading', { name: 'sample-london' })).toBeVisible())
    await screen.findByAltText('Proposal P002')
    act(() => history.forward())
    await waitFor(() => expect(screen.getByRole('heading', { name: 'New project' })).toBeVisible())
    expect(fetch).toHaveBeenCalledTimes(4)
  })
})
