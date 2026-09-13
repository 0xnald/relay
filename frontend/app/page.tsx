import { CommandCenter } from "../components/command-center";
import { RuntimeStatus } from "../components/runtime-status";

export default function Home() {
  return <><div className="absolute right-6 top-5 z-10"><RuntimeStatus /></div><CommandCenter /></>;
}
