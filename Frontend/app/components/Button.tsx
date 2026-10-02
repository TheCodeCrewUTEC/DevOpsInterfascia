import Link from "next/link";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  href?: string;
  type?: "button" | "submit" | "reset";
  prefetch?: boolean;
  // Navegación completa del navegador (<a>) en vez de <Link>. Necesario para rutas que
  // redirigen a otro origen (Keycloak): el fetch RSC de <Link> no puede seguir esa redirección.
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
      ? "rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
      : "rounded-lg border border-blue-600 px-4 py-2 text-blue-600 hover:bg-blue-50";

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
