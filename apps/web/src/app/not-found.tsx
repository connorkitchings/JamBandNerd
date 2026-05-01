import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 px-4 text-center">
      <h1 className="text-4xl font-headline font-bold text-on-surface">404</h1>
      <h2 className="text-xl font-semibold text-on-surface">Page not found</h2>
      <p className="text-on-surface-variant max-w-md">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
        className="mt-2 px-6 py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-hover transition-colors"
      >
        Go home
      </Link>
    </div>
  );
}
