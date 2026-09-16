import Button from "../components/Button";

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-8 py-16">

      <div className="w-full max-w-sm border border-gray-300 bg-gray-100 p-8">

        <h1 className="mb-8 text-center text-2xl font-normal">
          Iniciar sesión
        </h1>

        <form className="flex flex-col gap-4">

          <div className="flex flex-col gap-1">
            <label htmlFor="usuario" className="text-sm">
              Usuario
            </label>
            <input
              id="usuario"
              name="usuario"
              type="text"
              className="border border-gray-400 bg-white px-3 py-2"
              required
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="contrasena" className="text-sm">
              Contraseña
            </label>
            <input
              id="contrasena"
              name="contrasena"
              type="password"
              className="border border-gray-400 bg-white px-3 py-2"
              required
            />
          </div>

          <div className="mt-4 flex flex-col gap-3">
            <Button type="submit">Ingresar</Button>
            <Button href="/" variant="secondary">Volver</Button>
          </div>

        </form>

      </div>

    </main>
  );
}
