#include "lmlm/capabilities.hpp"

#include <sstream>

namespace lmlm {
CpuCapabilities detect_cpu_capabilities() {
  CpuCapabilities result;
#if defined(__x86_64__) || defined(_M_X64)
  result.architecture = "x86_64";
#elif defined(__i386__) || defined(_M_IX86)
  result.architecture = "x86";
#elif defined(__aarch64__) || defined(_M_ARM64)
  result.architecture = "arm64";
#elif defined(__arm__) || defined(_M_ARM)
  result.architecture = "arm";
#else
  result.architecture = "unknown";
#endif

#if (defined(__GNUC__) || defined(__clang__)) && (defined(__x86_64__) || defined(__i386__))
  __builtin_cpu_init();
  result.sse2 = __builtin_cpu_supports("sse2");
  result.avx = __builtin_cpu_supports("avx");
  result.avx2 = __builtin_cpu_supports("avx2");
  result.avx512f = __builtin_cpu_supports("avx512f");
#elif defined(__SSE2__)
  result.sse2 = true;
#endif

#if defined(__aarch64__) || defined(__ARM_NEON) || defined(__ARM_NEON__)
  result.neon = true;
#endif
  return result;
}

std::string cpu_capabilities_json(const CpuCapabilities& c) {
  std::ostringstream out;
  out << "{\"backend\":\"cpu\",\"architecture\":\"" << c.architecture
      << "\",\"features\":{\"sse2\":" << (c.sse2 ? "true" : "false")
      << ",\"avx\":" << (c.avx ? "true" : "false")
      << ",\"avx2\":" << (c.avx2 ? "true" : "false")
      << ",\"avx512f\":" << (c.avx512f ? "true" : "false")
      << ",\"neon\":" << (c.neon ? "true" : "false") << "}}";
  return out.str();
}
}
