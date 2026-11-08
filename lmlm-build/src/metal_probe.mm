#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <iostream>

int main() {
  @autoreleasepool {
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    if (device == nil) {
      std::cout << "{\"backend\":\"metal\",\"available\":false,\"devices\":0}\n";
      return 0;
    }
    std::cout << "{\"backend\":\"metal\",\"available\":true,\"device\":\""
              << [[device name] UTF8String] << "\"}\n";
    return 0;
  }
}
