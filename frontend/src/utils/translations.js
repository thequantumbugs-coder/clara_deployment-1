export function translate(labelMap, lang) {
  if (!labelMap) return "";
  return labelMap[lang] ?? labelMap["en"] ?? "";
}
