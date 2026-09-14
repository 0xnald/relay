import { CommandCenter } from "../components/command-center";
import { RuntimeStatus } from "../components/runtime-status";

export default function Home() {
  return <CommandCenter headerExtra={<RuntimeStatus />} />;
}
