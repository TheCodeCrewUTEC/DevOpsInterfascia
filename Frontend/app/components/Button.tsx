import Link from "next/link";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  href?: string;
  type?: "button" | "submit" | "reset";
  prefetch?: boolean;
  // Enlace normal (no Link) para rutas que redirigen fuera de Next, como Keycloak
  recargar?: boolean;
}

export default function Button({
  children,
  variant = "primary",
  href,
  type = "button",
  prefetch,
  recargar = false,
}: ButtonProps) {
  const className =
    variant === "primary"
      ? "rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover"
      : "rounded-full border border-pine/40 bg-paper px-4 py-2 text-sm text-ink transition duration-200 hover:-translate-y-0.5 hover:border-pine hover:bg-foam";

  if (href && recargar) {
    return (
      <a href={href} className={`inline-block text-center ${className}`}>
        {children}
      </a>
    );
  }

  if (href) {
    return (
      <Link href={href} prefetch={prefetch} className={`inline-block text-center ${className}`}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} className={className}>
      {children}
    </button>
  );
}
