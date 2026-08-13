import type { NextConfig } from "next";

const allowedDevOrigins = process.env.NEXT_ALLOWED_DEV_ORIGINS?.split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  // The dashboard is opened from other devices on the local LAN during MVP
  // development. Next otherwise blocks its own HMR assets for that origin.
  allowedDevOrigins: allowedDevOrigins?.length ? allowedDevOrigins : ["192.168.15.9"],
};

export default nextConfig;
