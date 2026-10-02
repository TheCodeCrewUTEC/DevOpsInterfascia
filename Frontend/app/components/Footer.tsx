import Image from "next/image";

// width/height respetan la proporción real del archivo: si no, h-auto recalcula el alto y Next avisa
const logosFila1 = [
  { src: "/Logo_UTEC.png", alt: "Logo de UTEC", width: 90, height: 90 },
  { src: "/Logo_CURE.png", alt: "Logo de CURE", width: 120, height: 120 },
  { src: "/Logo_UDELAR.png", alt: "Logo de UDELAR", width: 90, height: 89 },
  { src: "/Logo_UTU1.png", alt: "Logo de UTU", width: 160, height: 23 },
];

const logosFila2 = [
  { src: "/Logo_MIDES.png", alt: "Logo de MIDES", width: 110, height: 62 },
  { src: "/Logo_MITURISMO.png", alt: "Logo de Ministerio de Turismo", width: 110, height: 65 },
  { src: "/LOGO_MIEM.jpg", alt: "Logo de MIEM", width: 110, height: 85 },
  { src: "/Logo_PROBIDES.png", alt: "Logo de PROBIDES", width: 100, height: 53 },
  { src: "/Logo_INEFOP.png", alt: "Logo de INEFOP", width: 100, height: 28 },
  { src: "/Logo_LATITUD.png", alt: "Logo de Latitud", width: 100, height: 58 },
];

const mitad = logos.length / 2;
const fila1 = logos.slice(0, mitad);
const fila2 = logos.slice(mitad);

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-pine/10 bg-pine-deep px-6 py-10 text-paper">
      <div className="mx-auto max-w-6xl">
        <p className="font-display text-lg">Avalado por</p>
        <p className="mt-1 text-sm text-paper/70">
          Instituciones que acompañan el piloto en el territorio.
        </p>

        <div className="mt-6 flex flex-col gap-3">
          <FilaLogos logos={fila1} />
          <FilaLogos logos={fila2} />
        </div>
      </div>
    </footer>
  );
}

function FilaLogos({
  logos,
}: {
  logos: { src: string; alt: string; width: number; height: number }[];
}) {
  return (
    <div className="grid grid-cols-5 items-center justify-items-stretch gap-3">
      {logos.map((logo) => (
        <div
          key={logo.src}
          className="flex h-16 items-center justify-center rounded-2xl bg-paper px-3 shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-md"
        >
          <Image
            src={logo.src}
            width={logo.width}
            height={logo.height}
            alt={logo.alt}
            className="h-9 w-auto max-w-full object-contain"
          />
        </div>
      ))}
    </div>
  );
}
