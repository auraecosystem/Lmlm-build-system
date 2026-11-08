#include "lmlm/capabilities.hpp"
#include <cassert>
#include <string>
int main() {
  const auto caps = lmlm::detect_cpu_capabilities();
  assert(!caps.architecture.empty());
  const auto json = lmlm::cpu_capabilities_json(caps);
  assert(json.find("\"backend\":\"cpu\"") != std::string::npos);
  assert(json.find("\"architecture\"") != std::string::npos);
  return 0;
}
