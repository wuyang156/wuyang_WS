#include <iostream>
#include <pluginlib/class_loader.hpp>
#include <polygon_base/polygon.hpp>

int main(int argc, char** argv)
{
  (void) argc;
  (void) argv;

  pluginlib::ClassLoader<polygon_base::RegularPolygon> poly_loader("polygon_base", "polygon_base::RegularPolygon");

  try
  {
    std::shared_ptr<polygon_base::RegularPolygon> square = poly_loader.createSharedInstance("polygon_plugins::Square");
    square->initialize(4.0);

    std::shared_ptr<polygon_base::RegularPolygon> triangle = poly_loader.createSharedInstance("polygon_plugins::Triangle");
    triangle->initialize(2.0);

    std::cout << "Triangle area: " << triangle->area() << std::endl;
    std::cout << "Square area: " << square->area() << std::endl;
  }
  catch (const pluginlib::PluginlibException & ex)
  {
    std::cerr << "The plugin failed to load for some reason. Error: " << ex.what() << std::endl;
  }
  catch (const std::exception & ex)
  {
    std::cerr << "Unexpected runtime error: " << ex.what() << std::endl;
  }

  return 0;
}
