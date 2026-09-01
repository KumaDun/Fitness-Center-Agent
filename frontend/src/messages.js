export function addMessage(container, kind, text) {
  const node = document.createElement("div");
  node.className = `message ${kind}`;
  node.textContent = text;
  container.appendChild(node);
  container.scrollTop = container.scrollHeight;
}
