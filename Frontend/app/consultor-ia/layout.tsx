import { auth } from "@/auth";
import { puedeConsultarIa } from "@/lib/roles";
import { redirect } from "next/navigation";

export default async function ConsultorLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  if (!puedeConsultarIa(session)) {
    redirect("/sin-acceso");
  }

  return children;
}
