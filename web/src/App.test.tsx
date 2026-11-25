import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

function openSample() {
  fireEvent.click(screen.getByRole('link', { name: 'sample-london' }))
}

function openSetup() {
  fireEvent.click(screen.getAllByRole('link', { name: 'New project' })[0])
}

async function suggestedMessage() {
  fireEvent.click(screen.getByRole('button', { name: /Use suggested message/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Send' }))
  await act(async () => { await vi.advanceTimersByTimeAsync(650) })
  await act(async () => { await vi.advanceTimersByTimeAsync(650) })
}

async function finishWalkthrough() {
  openSample()
  await suggestedMessage()
  await suggestedMessage()
  await suggestedMessage()
}

function files() {
  return [
    new File(['first'], 'first.jpg', { type: 'image/jpeg' }),
    new File(['second'], 'second.png', { type: 'image/png' }),
  ]
}

async function fillDraft(user: ReturnType<typeof userEvent.setup>, id: string) {
  openSetup()
  await user.type(screen.getByLabelText('Project ID'), id)
  await user.upload(screen.getByLabelText('Choose 2-6 photos'), files())
  fireEvent.load(screen.getByAltText('Selected photo 1'))
  fireEvent.load(screen.getByAltText('Selected photo 2'))
}

describe('frontend-only prototype', () => {
  beforeEach(() => {
    history.replaceState(null, '', '/')
    vi.useFakeTimers()
    let number = 0
    vi.stubGlobal('URL', class extends URL {
      static createObjectURL = vi.fn(() => `blob:local-${++number}`)
      static revokeObjectURL = vi.fn()
    })
  })

  it('validates file selection, numbers thumbnails, and releases replaced URLs', async () => {
    vi.useRealTimers()
    const user = userEvent.setup({ applyAccept: false })
    render(<App />)
    openSetup()
    const input = screen.getByLabelText('Choose 2-6 photos')
    const [first, second] = files()
    await user.upload(input, first)
    expect(screen.getByRole('alert')).toHaveTextContent('between 2 and 6')
    await user.upload(input, [first, new File(['bad'], 'bad.txt', { type: 'text/plain' })])
    expect(screen.getByRole('alert')).toHaveTextContent('JPEG or PNG')
    const oversized = new File(['photo'], 'large.jpg', { type: 'image/jpeg' })
    Object.defineProperty(oversized, 'size', { value: 25 * 1024 * 1024 + 1 })
    await user.upload(input, [first, oversized])
    expect(screen.getByRole('alert')).toHaveTextContent('25 MiB or smaller')
    await user.upload(input, [first, second])
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByAltText('Selected photo 1')).toHaveAttribute('src', 'blob:local-1')
    expect(screen.getByAltText('Selected photo 2')).toHaveAttribute('src', 'blob:local-2')
    expect(screen.queryByText('first.jpg')).not.toBeInTheDocument()
    await user.upload(input, Array.from({ length: 7 }, (_, index) =>
      new File(['photo'], `${index}.jpg`, { type: 'image/jpeg' })))
    expect(screen.getByRole('alert')).toHaveTextContent('between 2 and 6')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:local-1')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:local-2')
    expect(screen.queryByAltText('Selected photo 1')).not.toBeInTheDocument()
  })

  it('reports an unreadable local image and prevents creating a draft from it', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    const { unmount } = render(<App />)
    openSetup()
    await user.type(screen.getByLabelText('Project ID'), 'my-project')
    await user.upload(screen.getByLabelText('Choose 2-6 photos'), files())
    fireEvent.error(screen.getByAltText('Selected photo 1'))
    fireEvent.load(screen.getByAltText('Selected photo 2'))
    expect(screen.getByRole('alert')).toHaveTextContent('Could not display a selected photo')
    fireEvent.click(screen.getByRole('button', { name: 'Create browser draft' }))
    expect(location.pathname).toBe('/new')
    expect(screen.getAllByRole('alert').some((alert) => alert.textContent?.includes('readable photos'))).toBe(true)
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
  })

  it('keeps new-project settings and selected photos separate from the fixed sample', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    render(<App />)
    openSetup()
    await user.upload(screen.getByLabelText('Choose 2-6 photos'), files())
    await user.selectOptions(screen.getByLabelText('Canvas preset'), '16:9')
    fireEvent.click(screen.getByRole('link', { name: 'Projects' }))
    openSample()
    expect(location.pathname).toBe('/projects/sample-london')
    expect(screen.getByRole('heading', { name: 'sample-london' })).toBeVisible()
    expect(screen.getByText(/4 photos.*1200 x 1800 px/)).toBeVisible()
    expect(screen.queryByAltText('Selected photo 1')).not.toBeInTheDocument()
    expect(screen.getByAltText('Photo 1')).toHaveAttribute('src', '/demo/photo-1.jpg')
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('walks through visible intent/layout phases, a clarification, and a second proposal', async () => {
    render(<App />)
    openSample()
    fireEvent.click(screen.getByRole('button', { name: /Use suggested message/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(screen.getByText('Understanding your request (simulated)')).toBeVisible()
    expect(screen.getByLabelText('Your message')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Accept proposal' })).toBeDisabled()
    await act(async () => { await vi.advanceTimersByTimeAsync(650) })
    expect(screen.getByText('Creating your layout (simulated)')).toBeVisible()
    await act(async () => { await vi.advanceTimersByTimeAsync(650) })
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Continue from here: P001' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /Use suggested message/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await act(async () => { await vi.advanceTimersByTimeAsync(650) })
    expect(screen.getByText(/Change just the background to charcoal/)).toBeVisible()
    expect(screen.queryByText('Creating your layout (simulated)')).not.toBeInTheDocument()
    await suggestedMessage()
    expect(screen.getByAltText('Proposal P002')).toBeVisible()
    expect(screen.getAllByRole('button', { name: /Continue from here:/ })).toHaveLength(2)
    expect(screen.getByText('Sample walkthrough complete.')).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('rejects unsupported prompts without pretending to create a response or proposal', () => {
    render(<App />)
    openSample()
    fireEvent.change(screen.getByLabelText('Your message'), { target: { value: 'Make a collage of my cat' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Only the suggested sample message is supported')
    expect(within(screen.getByRole('log')).queryByText('Make a collage of my cat')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Continue from here:/ })).not.toBeInTheDocument()
  })

  it('keeps the sample usable after a failed backend check without further requests', async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError('Backend is stopped'))
    render(<App />)
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Check backend' }))
    })
    expect(screen.getByRole('alert')).toHaveTextContent('Backend is stopped')
    openSample()
    await suggestedMessage()
    expect(screen.getByAltText('Proposal P001')).toBeVisible()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('keeps acceptance independent from baseline navigation and retains later history', async () => {
    render(<App />)
    await finishWalkthrough()
    fireEvent.click(screen.getByRole('button', { name: 'Accept proposal' }))
    expect(screen.getByText('Accepted: P002 (this tab only)')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Continue from here: P001' }))
    expect(screen.getByText('Baseline: P001')).toBeVisible()
    expect(screen.getByText('Accepted: P002 (this tab only)')).toBeVisible()
    expect(screen.getByAltText('Proposal P002 thumbnail')).toBeVisible()
    expect(screen.getByRole('log')).toHaveTextContent('background is now charcoal')
    expect(screen.getByRole('link', { name: 'Download PNG' })).toHaveAttribute('href', '/demo/london-cream.png')
    expect(screen.getByRole('link', { name: 'Download PNG' })).toHaveAttribute('download', 'london-P001-sample.png')
    fireEvent.click(screen.getByRole('button', { name: 'Accept proposal' }))
    expect(screen.getByText('Accepted: P001 (this tab only)')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Your message'), { target: { value: 'Another collage please' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(screen.getByRole('alert')).toHaveTextContent('walkthrough is complete')
  })

  it('rejects conflicting actions during simulated work and cancels work on reset', async () => {
    render(<App />)
    openSample()
    await suggestedMessage()
    fireEvent.click(screen.getByRole('button', { name: /Use suggested message/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(screen.getByRole('button', { name: 'Continue from here: P001' })).toBeDisabled()
    expect(screen.getByRole('button', { name: /Use suggested message/ })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Reset prototype' }))
    await act(async () => { await vi.advanceTimersByTimeAsync(5000) })
    expect(location.pathname).toBe('/')
    expect(screen.getByRole('heading', { name: 'Projects' })).toBeVisible()
    openSample()
    expect(screen.queryByAltText('Proposal P001 thumbnail')).not.toBeInTheDocument()
    expect(screen.queryByText(/Change just the background/)).not.toBeInTheDocument()
  })

  it('resolves a sample deep link after remount with fresh state and no browser storage', async () => {
    const { unmount } = render(<App />)
    await finishWalkthrough()
    fireEvent.click(screen.getByRole('button', { name: 'Accept proposal' }))
    unmount()
    render(<App />)
    expect(screen.getByRole('heading', { name: 'sample-london' })).toBeVisible()
    expect(screen.queryByAltText('Proposal P002 thumbnail')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept proposal' })).toBeDisabled()
    expect(Storage.prototype.getItem).not.toHaveBeenCalled()
    expect(Storage.prototype.setItem).not.toHaveBeenCalled()
  })

  it('preserves sample history and acceptance while browsing other pages', async () => {
    render(<App />)
    await finishWalkthrough()
    fireEvent.click(screen.getByRole('button', { name: 'Accept proposal' }))
    fireEvent.click(screen.getByRole('link', { name: 'Projects' }))
    openSetup()
    fireEvent.click(screen.getByRole('link', { name: 'Cancel' }))
    openSample()
    expect(screen.getByRole('log')).toHaveTextContent('background is now charcoal')
    expect(screen.getByText('Accepted: P002 (this tab only)')).toBeVisible()
  })

  it('creates separately browseable drafts with custom pixels and retains their object URLs until reset', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    render(<App />)
    await fillDraft(user, 'my-project')
    fireEvent.change(screen.getByLabelText('Width (px)'), { target: { value: '2048' } })
    fireEvent.change(screen.getByLabelText('Height (px)'), { target: { value: '1024' } })
    expect(screen.getByLabelText('Canvas preset')).toHaveValue('custom')
    fireEvent.click(screen.getByRole('button', { name: 'Create browser draft' }))
    expect(location.pathname).toBe('/projects/my-project')
    expect(screen.getByRole('heading', { name: 'my-project' })).toBeVisible()
    expect(screen.getByText(/2 photos.*2048 x 1024 px/)).toBeVisible()
    expect(screen.getByAltText('Photo 1')).toHaveAttribute('src', 'blob:local-1')
    expect(screen.queryByLabelText('Your message')).not.toBeInTheDocument()
    expect(screen.queryByAltText(/Proposal/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Projects' }))
    await fillDraft(user, 'second-project')
    await user.selectOptions(screen.getByLabelText('Canvas preset'), '4:3')
    expect(screen.getByLabelText('Width (px)')).toHaveValue(1600)
    expect(screen.getByLabelText('Height (px)')).toHaveValue(1200)
    fireEvent.click(screen.getByRole('button', { name: 'Create browser draft' }))
    expect(location.pathname).toBe('/projects/second-project')
    fireEvent.click(screen.getByRole('link', { name: 'Projects' }))
    expect(screen.getByRole('link', { name: 'second-project' })).toBeVisible()
    fireEvent.click(screen.getByRole('link', { name: 'my-project' }))
    expect(screen.getByAltText('Photo 1')).toHaveAttribute('src', 'blob:local-1')
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Reset prototype' }))
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(4)
    expect(screen.queryByRole('link', { name: 'my-project' })).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('validates backend project IDs, duplicate IDs and integer canvas bounds before accepting a draft', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    render(<App />)
    await fillDraft(user, 'UPPER')
    const submit = screen.getByRole('button', { name: 'Create browser draft' })
    const id = screen.getByLabelText('Project ID')
    fireEvent.click(submit)
    expect(screen.getByRole('alert')).toHaveTextContent('lowercase letters')
    fireEvent.change(id, { target: { value: 'con' } })
    fireEvent.click(submit)
    expect(screen.getByRole('alert')).toHaveTextContent('reserved Windows device name')
    fireEvent.change(id, { target: { value: 'sample-london' } })
    fireEvent.click(submit)
    expect(screen.getByRole('alert')).toHaveTextContent('already in use')
    fireEvent.change(id, { target: { value: 'valid-project' } })
    for (const [label, value] of [
      ['Width (px)', '0'], ['Width (px)', '4097'], ['Width (px)', '12.5'], ['Width (px)', ''],
      ['Height (px)', '0'], ['Height (px)', '4097'], ['Height (px)', '12.5'],
    ]) {
      fireEvent.change(screen.getByLabelText('Width (px)'), { target: { value: '1200' } })
      fireEvent.change(screen.getByLabelText('Height (px)'), { target: { value: '1800' } })
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
      fireEvent.click(submit)
      expect(screen.getByRole('alert')).toHaveTextContent('whole pixels from 1 to 4096')
      expect(location.pathname).toBe('/new')
    }
    fireEvent.change(screen.getByLabelText('Width (px)'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Height (px)'), { target: { value: '4096' } })
    fireEvent.click(submit)
    expect(screen.getByText(/2 photos.*1 x 4096 px/)).toBeVisible()
  })

  it('supports browser back/forward and explains missing project deep links', async () => {
    vi.useRealTimers()
    const { unmount } = render(<App />)
    openSample()
    openSetup()
    act(() => history.back())
    await waitFor(() => expect(screen.getByRole('heading', { name: 'sample-london' })).toBeVisible())
    act(() => history.forward())
    await waitFor(() => expect(screen.getByRole('heading', { name: 'New project' })).toBeVisible())
    unmount()
    history.replaceState(null, '', '/projects/missing-draft')
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Project or page not found' })).toBeVisible()
    expect(screen.getByText(/Browser drafts are cleared on refresh/)).toBeVisible()
    expect(screen.queryByRole('log')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Back to projects' }))
    expect(location.pathname).toBe('/')
  })
})
