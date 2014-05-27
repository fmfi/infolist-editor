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
  function toggleBlok(blok) {
    var body = $(blok).children('.panel-body');
    var link = $(blok).find('.panel-heading a.toggle');
    body.toggleClass('zbaleny');
    if (body.hasClass('zbaleny')) {
      link.text('Rozbaliť blok');
    }
    else {
      link.text('Zbaliť blok');
    }
  }
  $(".blok").each(function(index, blok) {
    var nazov = $(blok).find('[name=nazov]');
    var heading = $(blok).find('.panel-heading .title').text($(nazov[0]).val());
    toggleBlok(blok);
  });
  $(document).on('input paste keyup', '.blok [name=nazov]', function() {
    $(this).closest('.blok').find('.panel-heading .title').text($(this).val());
  });
  $(document).on('click', '.blok .panel-heading a.toggle', function(event) {
    toggleBlok($(this).closest('.blok'));
    event.preventDefault();
  });
});