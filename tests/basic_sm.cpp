#include <boost/sml.hpp>

using namespace boost::sml;
namespace sml = boost::sml;

struct e1{};
struct e2{};

struct a1 {
    void operator()(){}
};


struct a2 {
    void operator()(){}
};

struct g1 {
    bool operator()(){ return true;}
};

struct g2 {
    bool operator()(){ return true;}
};


struct s0 {                             // Sub level SM
  auto operator()() noexcept {
    auto idle = state<struct s0_idle_>; // Leaf state
    auto run = state<struct run_>;      // Leaf state
    auto run2 = state<struct run2_>;    // Leaf state
    return make_transition_table(
        *idle = run                     // Anonymous transition
      , run + on_entry<_> / []{}        // Lambda on entry
      , run + sml::on_exit<_> / a2{}    // Functor on exit
      , run + event<e1> / a1{} = run2   // Functor on event + transition
    );
  }
};

struct s1 {                             // Top level SM
  auto operator()() noexcept {
    auto idle = state<struct s1_idle_>; // Leaf state
    auto S_s0 = state<s0>;              // Sub state
    auto S_none = state<struct none_>;  // Leaf state
    return make_transition_table(
        *idle = S_s0                    // Anonymous transition
      , S_s0 + on_entry<_> / []{}       // Lambda on entry
      , S_s0 + event<e2> = S_none       // Transition on event
      , S_s0 + event<e1> [g1{}] / a1{}  // Action on event with guard
      , S_none [g1{}] / a2{}            // Anonimous guard + action
      , S_none [g2{}] = S_s0              // Anonimous guard + action
    );
  }
};


int main() {
    auto my_sm = boost::sml::sm<s1>{};
}