export const categories = ["top", "bottom", "dress", "outerwear", "footwear", "accessory"];

export type Piece = { item_id: string; category: string; title: string | null; image_url: string };
export type Match = Piece & { similarity: number };
export type Result = { recommendations: Match[]; alternatives?: Record<string, Match[]>; warnings: string[] };
export type Look = { id: string; name: string; original: Piece; matches: Match[] };

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/${path}`, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message ?? "The stylist is unavailable. Please try again.");
  return data;
}

export function imageData(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("This photo could not be read."));
    reader.readAsDataURL(file);
  });
}

export async function downloadLook(original: Piece, matches: Match[]) {
  const pieces = [original, ...matches];
  const images = await Promise.all(pieces.map(async piece => {
    const image = new Image();
    image.src = piece.image_url;
    await image.decode();
    return image;
  }));
  const canvas = document.createElement("canvas");
  canvas.width = 1600;
  canvas.height = 1300;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Image export is unavailable.");
  ctx.fillStyle = "#FAF2EE";
  ctx.fillRect(0, 0, 1600, 1300);
  ctx.fillStyle = "#3C2030";
  ctx.font = "64px Georgia";
  ctx.fillText("AI Outfit Stylist", 80, 100);
  images.forEach((image, index) => {
    const x = 80 + (index % 2) * 740;
    const y = 150 + Math.floor(index / 2) * 560;
    ctx.fillStyle = "#fffaf8";
    ctx.fillRect(x, y, 700, 495);
    const scale = Math.min(660 / image.width, 455 / image.height);
    const w = image.width * scale;
    const h = image.height * scale;
    ctx.drawImage(image, x + (700 - w) / 2, y + (495 - h) / 2, w, h);
    ctx.fillStyle = "#3C2030";
    ctx.font = "28px Georgia";
    ctx.fillText(index ? pieces[index].category : "Your original piece", x, y + 535);
  });
  const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("The outfit image could not be exported.");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "my-stylist-look.png";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
