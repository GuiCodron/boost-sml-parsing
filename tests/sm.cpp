#include <boost/sml.hpp>

namespace sml = boost::sml;

struct e1 {};
struct e2 {};
struct e3 {};
struct e4 {};
struct e5 {};
struct e6 {};

const auto idle = sml::state<class idle>;
const auto idle2 = sml::state<class idle2>;
const auto s1 = sml::state<class s1>;
const auto s2 = sml::state<class s2>;

static auto guard = []() { return true; };

struct guard2 {
  bool operator()() const { return true; }
};

struct sub {
  auto operator()() noexcept {
    using namespace sml;

    // clang-format off
      return make_transition_table(
         *idle + event<e3> / [this] { a_in_sub++; } = s1
        , s1 + event<e4> / [this] { a_in_sub++; } = s2
      );
    // clang-format on
  }

  int a_in_sub = 0;
};

struct c {
  auto operator()() noexcept {
    using namespace sml;

    // clang-format off
      return make_transition_table(
         *idle + event<e1> [(guard2{})] / [this] { a_initial = true; } = s1
        , s1 + event<e2> [guard]  / [this]{ a_enter_sub_sm = true; } = state<sub>
        , state<sub> + sml::on_entry<_> / [this] { a_on_entry_sub_sm = true; }
        , state<sub> + sml::on_exit<_> / [this] { a_on_exit_sub_sm = true; }
        , state<sub> + event<e5> [(guard2{})] / [this] { a_exit_sub_sm = true; } = s2
      );
    // clang-format on
  }

  bool a_initial = false;
  bool a_enter_sub_sm = false;
  bool a_exit_sub_sm = false;
  bool a_on_exit_sub_sm = false;
  bool a_on_entry_sub_sm = false;
};

int main() { sml::sm<c> sm; }
