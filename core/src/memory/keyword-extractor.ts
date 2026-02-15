/**
 * KeywordExtractor — lightweight keyword extraction for memory relevance matching.
 *
 * Supports Chinese + English text. No external NLP dependencies.
 * - Chinese: split by common delimiters, filter short fragments
 * - English: split by whitespace, remove stop words
 * - Returns deduplicated, lowercased keyword array
 */

const EN_STOP_WORDS = new Set([
  "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
  "have", "has", "had", "do", "does", "did", "will", "would", "could",
  "should", "may", "might", "can", "shall", "to", "of", "in", "for",
  "on", "with", "at", "by", "from", "as", "into", "about", "between",
  "through", "during", "before", "after", "above", "below", "up", "down",
  "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
  "neither", "each", "every", "all", "any", "few", "more", "most",
  "other", "some", "such", "no", "only", "same", "than", "too", "very",
  "just", "because", "if", "when", "while", "where", "how", "what",
  "which", "who", "whom", "this", "that", "these", "those", "i", "me",
  "my", "we", "our", "you", "your", "he", "him", "his", "she", "her",
  "it", "its", "they", "them", "their",
]);

const ZH_STOP_WORDS = new Set([
  "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
  "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
  "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
]);

// Regex to split Chinese text into character n-grams and word-like units
const ZH_CHAR_RE = /[\u4e00-\u9fff]/g;
const EN_WORD_RE = /[a-zA-Z]{2,}/g;

/**
 * Extract keywords from a text string.
 * Returns an array of unique lowercase keywords.
 */
export function extractKeywords(text: string): string[] {
  if (!text || text.trim().length === 0) return [];

  const keywords = new Set<string>();

  // Extract English words
  const enMatches = text.match(EN_WORD_RE);
  if (enMatches) {
    for (const word of enMatches) {
      const lower = word.toLowerCase();
      if (!EN_STOP_WORDS.has(lower)) {
        keywords.add(lower);
      }
    }
  }

  // Extract Chinese characters/bigrams
  const zhChars = text.match(ZH_CHAR_RE);
  if (zhChars) {
    // Single chars (filter stop words)
    for (const ch of zhChars) {
      if (!ZH_STOP_WORDS.has(ch)) {
        keywords.add(ch);
      }
    }
    // Bigrams for better matching
    for (let i = 0; i < zhChars.length - 1; i++) {
      const bigram = zhChars[i] + zhChars[i + 1];
      if (!ZH_STOP_WORDS.has(bigram)) {
        keywords.add(bigram);
      }
    }
  }

  return Array.from(keywords);
}

/**
 * Compute relevance score between a set of query keywords and an entry's tags + summary.
 */
export function computeRelevanceScore(
  queryKeywords: string[],
  tags: string[],
  summary: string
): number {
  if (queryKeywords.length === 0) return 0;

  let score = 0;
  const lowerTags = tags.map((t) => t.toLowerCase());
  const lowerSummary = summary.toLowerCase();

  for (const kw of queryKeywords) {
    // Tag match: higher weight
    if (lowerTags.includes(kw)) {
      score += 3;
    }
    // Summary keyword match
    if (lowerSummary.includes(kw)) {
      score += 1;
    }
  }

  return score;
}
