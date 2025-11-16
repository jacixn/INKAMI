export default function DocsPage() {
  return (
    <div className="card space-y-4">
      <h1 className="text-3xl font-semibold text-white">Developer Docs</h1>
      <p className="text-ink-100">
        Formal API and pipeline docs live in the repo&apos;s `/docs` folder.
        This placeholder route links there for convenience while the dedicated
        documentation UI is still in progress.
      </p>
      <ul className="list-disc space-y-2 pl-5 text-sm text-ink-100">
        <li>
          <a
            href="https://github.com/"
            className="text-white underline"
            target="_blank"
            rel="noreferrer"
          >
            Open repo docs
          </a>
        </li>
        <li>COMING SOON: live API explorer + webhook logs.</li>
      </ul>
    </div>
  );
}

