(function() {
  var blokInfolist = function(element) {
    if (!(this instanceof blokInfolist))
      return new blokInfolist(element);

    var values = JSON.parse(element.attr('data-values'));
    
  }
  $.fn.blokInfolist = function() {
    new blokInfolist(this);
  };
})();

$(document).ready(function(){
  $(".blok").each(function(index, blok) {
    var nazov = $(blok).find('[name=nazov]');
    var heading = $(blok).find('.panel-heading .title').text($(nazov[0]).val());
  });
  $(document).on('input paste keyup', '.blok [name=nazov]', function() {
    $(this).closest('.blok').find('.panel-heading .title').text($(this).val());
  });
  $(document).on('click', '.blok .panel-heading a.toggle', function(event) {
    var body = $(this).closest('.blok').children('.panel-body');
    body.toggleClass('zbaleny');
    if (body.hasClass('zbaleny')) {
      $(this).text('Rozbaliť blok');
    }
    else {
      $(this).text('Zbaliť blok');
    }
    event.preventDefault();
  });
});