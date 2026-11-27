import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import App from "./App.jsx";
import "./App.css";

// Dos direcciones: «/» (conversación nueva) y «/c/<hilo>» (una conversación guardada). La pantalla es la ruta padre y las dos direcciones
// son hijas, así que al crearse el hilo la pantalla no se vuelve a montar ni pierde lo que se está escribiendo.
// Cualquier otra dirección también la recibe la pantalla, que la lleva a «/». Las hijas no pintan nada (`element={null}`): sin él, el
// enrutador deja un aviso en la consola.
createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />}>
        <Route index element={null} />
        <Route path="c/:hilo" element={null} />
        <Route path="*" element={null} />
      </Route>
    </Routes>
  </BrowserRouter>,
);
