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