import type { Message } from "@langchain/langgraph-sdk";

/**
 * Extracts a string summary from a message's content, supporting multimodal (text, image, file, etc.).
 * - If text is present, returns the joined text.
 * - If not, returns a label for the first non-text modality (e.g., 'Image', 'Other').
 * - If unknown, returns 'Multimodal message'.
 */
export function getContentString(content: Message["content"]): string {
  if (typeof content === "string") return content;
  const texts = content
    .filter((c): c is { type: "text"; text: string } => c.type === "text")
    .map((c) => c.text);
  // Preserve markdown structure (line breaks, lists, headings) across chunks.
  return texts.join("");
}

/**
 * Extracts thinking content from a message string that uses <think>...</think> tags.
 * Also handles partial/streaming thinking blocks (no closing tag yet).
 *
 * Returns:
 * - `thinking`: the content inside <think> tags, or null if none found.
 * - `isThinkingStreaming`: true when the closing </think> tag has not yet appeared.
 * - `text`: the remaining text after the thinking block.
 */
export function extractThinkingAndText(content: string): {
  thinking: string | null;
  isThinkingStreaming: boolean;
  text: string;
} {
  // Complete thinking block
  const completeMatch = content.match(/^<think>([\s\S]*?)<\/think>\s*/);
  if (completeMatch) {
    return {
      thinking: completeMatch[1].trim(),
      isThinkingStreaming: false,
      text: content.slice(completeMatch[0].length),
    };
  }

  // Incomplete/streaming thinking block (no closing tag yet)
  const openMatch = content.match(/^<think>([\s\S]*)$/);
  if (openMatch) {
    return {
      thinking: openMatch[1],
      isThinkingStreaming: true,
      text: "",
    };
  }

  return { thinking: null, isThinkingStreaming: false, text: content };
}
