import EditorFormulario from "../EditorFormulario";

export default async function PaginaFormulario({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  const id = Number(jobId);

  if (!Number.isInteger(id)) {
    return (
      <main className="px-6 py-16">
        <p className="text-clay">No encontramos ese formulario.</p>
      </main>
    );
  }

  return <EditorFormulario jobId={id} />;
}
