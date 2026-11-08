#include "lmlm/build_info.hpp"
#include <cstring>
int main() {
  return std::strcmp(lmlm::build_fabric_version(), "0.1.0") == 0 ? 0 : 1;
}
