import Link from "next/link";

interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
  href?: string;
  type?: "button" | "submit" | "reset";
  onClick?: () => void;
  prefetch?: boolean;
}

export default function Button({
  children,
  variant = "primary",
  href,
  type = "button",
  onClick,
  prefetch,
}: ButtonProps) {
  const className =
    variant === "primary"
      ? "rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover"
      : "rounded-full border border-pine/40 bg-paper px-4 py-2 text-sm text-ink transition duration-200 hover:-translate-y-0.5 hover:border-pine hover:bg-foam";

  if (href) {
    return (
      <Link href={href} prefetch={prefetch} className={`inline-block text-center ${className}`}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} onClick={onClick} className={className}>
      {children}
    </button>
  );
}
