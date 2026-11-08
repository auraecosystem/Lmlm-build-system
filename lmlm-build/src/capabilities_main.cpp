#include "lmlm/capabilities.hpp"
#include <iostream>
int main() {
  std::cout << lmlm::cpu_capabilities_json(lmlm::detect_cpu_capabilities()) << '\n';
  return 0;
}
