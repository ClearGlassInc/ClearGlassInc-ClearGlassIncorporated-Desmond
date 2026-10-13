import type { Metadata } from "next";
import ChualarOperations from "./ChualarOperations";

export const metadata: Metadata = {
  title: "Chualar — Monterey County Live Operations | ClearGlass",
  description: "Public-source geospatial operations dashboard for the Chualar area. Source health and live counts are reported from provider responses.",
};
export default function ChualarPage(): React.JSX.Element {
  return <ChualarOperations />;
}
