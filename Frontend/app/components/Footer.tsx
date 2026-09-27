import Image from "next/image";

const logosFila1 = [
  { src: "/Logo_UTEC.png", alt: "Logo de UTEC", width: 90, height: 85 },
  { src: "/Logo_CURE.png", alt: "Logo de CURE", width: 120, height: 60 },
  { src: "/Logo_UDELAR.png", alt: "Logo de UDELAR", width: 90, height: 65 },
  { src: "/Logo_UTU1.png", alt: "Logo de UTU", width: 160, height: 60 },
];

const logosFila2 = [
  { src: "/Logo_MIDES.png", alt: "Logo de MIDES", width: 110, height: 55 },
  { src: "/Logo_MITURISMO.png", alt: "Logo de Ministerio de Turismo", width: 110, height: 55 },
  { src: "/LOGO_MIEM.jpg", alt: "Logo de MIEM", width: 110, height: 55 },
  { src: "/Logo_PROBIDES.png", alt: "Logo de PROBIDES", width: 100, height: 55 },
  { src: "/Logo_INEFOP.png", alt: "Logo de INEFOP", width: 100, height: 55 },
  { src: "/Logo_LATITUD.png", alt: "Logo de Latitud", width: 100, height: 55 },
];

export default function Footer() {
  return (
    <footer className="mt-auto bg-white px-8 py-6">

      <div className="text-left">
        <p className="text-sm text-neutral-500">Avalado por</p>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
        {logosFila1.map((logo) => (
          <Image
            key={logo.src}
            src={logo.src}
            width={logo.width}
            height={logo.height}
            alt={logo.alt}
            className="h-auto object-contain"
          />
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        {logosFila2.map((logo) => (
          <Image
            key={logo.src}
            src={logo.src}
            width={logo.width}
            height={logo.height}
            alt={logo.alt}
            className="h-auto object-contain"
          />
        ))}
      </div>

    </footer>
  );
}
