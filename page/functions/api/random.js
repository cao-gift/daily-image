export default async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const format = url.searchParams.get("format") || "webp";

  if (!["webp", "jpeg", "original"].includes(format)) {
    return new Response("Invalid format parameter", { status: 400 });
  }

  // 从当前请求的域名拼接 JSON 地址
  const host = url.origin;
  const jsonUrl = `${host}/picture/index.json`;

  // 直接 fetch JSON（EO 会自己命中缓存）
  const fetchResp = await fetch(new Request(jsonUrl, request));
  if (!fetchResp.ok) {
    return new Response("Failed to load index.json", { status: 502 });
  }

  let images = await fetchResp.json();

  if (!Array.isArray(images) || images.length === 0) {
    return new Response("No images available", { status: 404 });
  }

  // 去掉最后一张，防止过期
  if (images.length > 1) {
    images = images.slice(0, -1);
  }

  // 随机挑一张
  const randomImage = images[Math.floor(Math.random() * images.length)];
  const redirect = url.searchParams.get("redirect") === "true";

  const imagePath = format === "jpeg"
    ? (randomImage.jpeg_path || `/picture/${randomImage.date}.jpeg`)
    : format === "original"
      ? (randomImage.original_path || `/picture/${randomImage.date}-original.jpeg`)
      : randomImage.path;
  const imageUrl = new URL(imagePath, request.url);

  if (redirect) {
    // 🚀 302 跳转
    return Response.redirect(imageUrl.toString(), 302);
  }

  // 🖼 直接返回图片二进制，走 EO 节点缓存
  const resp = await fetch(new Request(imageUrl.toString(), request));
  if (!resp.ok) {
    return new Response("Failed to fetch image", { status: 502 });
  }

  return new Response(resp.body, {
    headers: {
      "Content-Type": resp.headers.get("Content-Type") || (format === "webp" ? "image/webp" : "image/jpeg"),
      "Cache-Control": "public, max-age=10800", // 浏览器缓存 3 小时
      "bing-cache": "EO-FETCH", // 标识 EO fetch 命中
    },
  });
}
