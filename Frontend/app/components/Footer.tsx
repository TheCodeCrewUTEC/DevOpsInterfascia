import Link from "next/link";
import Button from "./Button";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="relative px-8 py-6">
      
      <div className="text-left">
        <p>Avalado por:</p>
      </div>

      <div className="flex justify-between items-center">
        <Image
          src="/Logo_UTEC.png"
          width={103}
          height={97}
          alt="Logo de UTEC"
        />

        <Image
          src="/Logo_CURE.png"
          width={140}
          height={69}
          alt="Logo de CURE"
        />

        <Image
          src="/Logo_UDELAR.png"
          width={100}
          height={73}
          alt="Logo de UDELAR"
        />

        <Image
          src="/Logo_UTU1.png"
          width={200          }
          height={73}
          alt="Logo de UTU"
        />
      </div>

    </footer>
  );
}