$(document).ready(function() {
  (function loop(){
    setTimeout(function() {
      $.ajax('{{ url_for("auth.ping") }}');
      loop();
    }, 5 * 60 * 1000);
  })();
});