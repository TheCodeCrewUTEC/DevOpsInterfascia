import Link from "next/link";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  href?: string;
  type?: "button" | "submit" | "reset";
}

export default function Button({
  children,
  variant = "primary",
  href,
  type = "button",
}: ButtonProps) {
  const className =
    variant === "primary"
      ? "rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
      : "rounded-lg border border-blue-600 px-4 py-2 text-blue-600 hover:bg-blue-50";

  if (href) {
    return (
      <Link href={href} className={`inline-block text-center ${className}`}>
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
