import React from "react";
import Particles from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";

const ParticlesBackground = () => {
  const particlesInit = async (engine) => {
    await loadSlim(engine);
  };

  return (
    <Particles
      id="tsparticles"
      init={particlesInit}
      options={{
        background: {
          color: {
            value: "#0d47a1", // Deep blue snowy background
          },
        },
        fpsLimit: 60,
        particles: {
          number: {
            value: 100,
          },
          color: {
            value: "#ffffff",
          },
          shape: {
            type: "circle",
          },
          opacity: {
            value: 0.8,
          },
          size: {
            value: { min: 2, max: 6 },
          },
          move: {
            enable: true,
            speed: 1,
            direction: "bottom",
            straight: false,
            outModes: {
              default: "out",
            },
          },
        },
        detectRetina: true,
      }}
    />
  );
};

export default ParticlesBackground;
