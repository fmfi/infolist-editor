$(document).ready(function() {
  (function loop(){
    setTimeout(function() {
      $.ajax('{{ url_for("ping") }}');
      loop();
    }, 5 * 60 * 1000);
  })();
});