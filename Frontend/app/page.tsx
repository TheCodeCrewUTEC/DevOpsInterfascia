import Image from "next/image";
import Button from "./components/Button";

export default function Home() {
  return (
    <main>

      {/* HERO */}
      <section className="px-8 py-10">

        <h1 className="max-w-3xl text-5xl font-normal leading-tight">
          Impulsando la innovación en el territorio uruguayo
        </h1>

        <div className="mt-8 flex items-center justify-between">

          <div className="h-64 w-1/2 bg-gray-200">
            Imagen
          </div>

          <div className="flex flex-col items-center gap-2">
            <p className="text-xs">
              ¿No tienes una cuenta aún?
            </p>

              <Button variant="secondary">Registrate</Button>
          </div>

        </div>

      </section>


      {/* ¿QUÉ ES INTERFASCIA? */}
      <section className="px-8 py-16">

        <div className="flex items-center gap-4">

          <div className="h-px flex-1 bg-black" />

          <h2 className="text-2xl font-normal">
            ¿Qué es Interfascia?
          </h2>

          <div className="h-px flex-1 bg-black" />

        </div>

        <p className="mx-auto mt-8 max-w-3xl text-center">
          Lorem ipsum dolor sit amet, consectetur adipiscing elit.
          Vivamus at facilisis arcu, finibus auctor arcu. Aenean a
          ante nisi. Phasellus eros mi, maximus et tellus vel,
          lacinia aliquet risus. Etiam faucibus laoreet placerat.
        </p>


        {/* Imágenes */}
        <div className="mt-10 flex items-center justify-center gap-12">

          <div className="h-32 w-64 bg-gray-200">
            Imagen
          </div>

          <div className="flex h-32 w-24 items-center justify-center bg-gray-300">
            LOGO
          </div>

          <div className="h-32 w-64 bg-gray-200">
            Imagen
          </div>

        </div>

      </section>
    </main>
  );
}