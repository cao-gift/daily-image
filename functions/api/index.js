export default async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  const base = `${url.protocol}//${url.host}`;

  const html = `
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>图片 API 服务</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 720px;
      margin: 2rem auto;
      padding: 1rem;
      line-height: 1.6;
    }
    h1 { color: #333; }
    code { background: #f4f4f4; padding: 0.2rem 0.4rem; border-radius: 4px; }
    .endpoint { margin-bottom: 1.5rem; }
  </style>
</head>
<body>
  <h1>📷 图片 API 服务</h1>
  <p>提供 <strong>随机图像</strong>、<strong>今日图像</strong> 和历史日期图像接口。</p>

  <div class="endpoint">
    <h2>/api/random</h2>
    <ul>
      <li><code>${base}/api/random</code> → 随机图片（默认 <strong>不重定向</strong>）</li>
      <li><code>${base}/api/random?redirect=true</code> → 随机图片（使用重定向）</li>
    </ul>
  </div>

  <div class="endpoint">
    <h2>/api/daily</h2>
    <ul>
      <li><code>${base}/api/daily</code> → 今日图像（默认 WebP，不重定向）</li>
      <li><code>${base}/api/daily?format=jpeg</code> → 压缩 JPEG</li>
      <li><code>${base}/api/daily?redirect=true</code> → 今日图像（使用重定向）</li>
      <li><code>${base}/api/daily?date=YYYY-MM-DD</code> → 指定日期的 WebP</li>
    </ul>
  </div>

  <footer>
    <p style="margin-top:2rem; color:#777;">Powered by EO Page Functions</p>
  </footer>
</body>
</html>
  `;

  return new Response(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
