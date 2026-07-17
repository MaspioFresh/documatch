  import { createRoot } from "react-dom/client";
  import App from "./app/App.tsx";
  import "./styles/index.css";
  import { DialogProvider } from "./app/components/DialogProvider.tsx";

  createRoot(document.getElementById("root")!).render(
    <DialogProvider>
      <App />
    </DialogProvider>
  );