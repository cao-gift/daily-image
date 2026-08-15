export default async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);

  // 处理参数
  const format = url.searchParams.get("format") || "webp";
  const date = url.searchParams.get("date");
  const redirect = url.searchParams.get("redirect") === "true";

  // 验证参数
  const allowedFormats = ["webp", "jpeg"];
  if (!allowedFormats.includes(format)) {
    return new Response("Invalid format parameter", { status: 400 });
  }
  if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return new Response("Invalid date parameter, expected YYYY-MM-DD", { status: 400 });
  }
  if (date && format === "jpeg") {
    return new Response("Historical JPEG is unavailable; use WebP for dated images", { status: 400 });
  }

  // 未指定日期时保持今日图片接口兼容；指定日期时读取历史图片。
  let imagePath;
  if (date) {
    imagePath = `/picture/${date}.webp`;
  } else {
    imagePath = format === "jpeg"
      ? "/daily.jpeg"
      : "/daily.webp";
  }

  // 构造目标 URL
  const imageUrl = new URL(request.url);
  imageUrl.pathname = imagePath;

  // 如果需要重定向
  if (redirect) {
    return Response.redirect(imageUrl.toString(), 302);
  }

  // 第一次请求：带 Request 对象，可命中 EdgeOne 缓存
  let originResponse = await fetch(new Request(imageUrl.toString(), request));

  // 第二次请求：直连 origin
  if (!originResponse.ok) {
    originResponse = await fetch(imageUrl.toString());
    if (!originResponse.ok) {
      const status = originResponse.status === 404 ? 404 : 502;
      return new Response(date ? "Image not found for requested date" : "Origin fetch failed", { status });
    }
  }

  // 返回响应（复制 headers + body）
  const response = new Response(originResponse.body, originResponse);
  response.headers.set("bing-cache", originResponse.redirected ? "BYPASS" : "EDGEONE");
  response.headers.set("Cache-Control", date ? "public, max-age=864000" : "public, max-age=10800");

  return response;
}
