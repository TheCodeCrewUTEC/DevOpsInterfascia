interface ButtonProps {
  children: React.ReactNode;
  variant?: "primary" | "secondary";
}

export default function Button({
  children,
  variant = "primary",
}: ButtonProps) {
  return (
    <button
      className={
        variant === "primary"
          ? "rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          : "rounded-lg border border-blue-600 px-4 py-2 text-blue-600 hover:bg-blue-50"
      }
    >
      {children}
    </button>
  );
}
