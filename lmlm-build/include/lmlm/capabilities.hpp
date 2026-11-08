#pragma once

#include <string>
#include <vector>

namespace lmlm {
struct CpuCapabilities {
  std::string architecture;
  bool sse2 = false;
  bool avx = false;
  bool avx2 = false;
  bool avx512f = false;
  bool neon = false;
};
CpuCapabilities detect_cpu_capabilities();
std::string cpu_capabilities_json(const CpuCapabilities& capabilities);
}
