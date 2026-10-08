export default function NotFound() {
  return (
    <div className="glass p-6">
      <h1>Not found</h1>
      <p className="muted mt-2">That record does not exist, or the link is out of date.</p>
      <p className="mt-4">
        <a href="/">Back to the overview</a>
      </p>
    </div>
  );
}
