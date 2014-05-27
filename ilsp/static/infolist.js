$(document).ready(function(){
  $(".filter-field select").select2({
    minimumResultsForSearch: 5
  });
  $("form.document-delete").on('submit', function(e) {
    var doc = $(e.target).data('delete-doc');
    if (!window.confirm('Naozaj zmazať ' + doc + '?')) {
      e.preventDefault();
    }
  });
});
(function() {
  var TokenStream = function(text) {
    if (!(this instanceof TokenStream))
      return new TokenStream(text);
    
    var tokens = text.split(' ');
    if (text == '') tokens = [];
    var index = 0;
    
    this.getOne = function() {
      if (index >= tokens.length) {
        return null;
      }
      return tokens[index++];
    }
    
    this.peek = function() {
      if (index >= tokens.length) {
        return null;
      }
      return tokens[index];
    }
    
    this.idx = function() {
      return index;
    }
  };
  
  var Errors = function() {
    if (!(this instanceof Errors))
      return new Errors(text);
    
    var errors = [];
    
    this.add = function(index, text) {
      errors.push({
        index: index,
        text: text,
        before: false
      });
    }
    
    this.addBefore = function(index, text) {
      errors.push({
        index: index,
        text: text,
        before: true
      });
    }
    
    this.getAll = function() {
      return errors;
    }
  };
  
  function parse_expr(tokens, errors) {
    var first = tokens.peek();
    
    if (first == '(') {
      tokens.getOne();
      parse_expr_in(tokens, errors);
      var last = tokens.getOne();
      if (last !== ')') {
        errors.addBefore(tokens.idx(), 'Očakávame pravú zátvorku');
      }
    }
    else if (/^[0-9]+$/.test(first)) {
      tokens.getOne();
    }
    else {
      errors.addBefore(tokens.idx(), 'Očakávame predmet alebo ľavú zátvorku');
    }
  }
  
  function parse_expr_in(tokens, errors) {
    parse_expr(tokens, errors);
    
    if (tokens.peek() === null || tokens.peek() == ')') {
      return;
    }
    
    var typ = tokens.peek();
    if (!(typ == 'OR' || typ == 'AND')) {
      errors.addBefore(tokens.idx(), 'Očakávame spojku "a" alebo "alebo"');
      parse_expr_in(tokens, errors);
      return;
    }
    tokens.getOne();
    
    while (true) {
      parse_expr(tokens, errors);
      
      var typ2 = tokens.peek();
      
      if (typ2 === null || typ2 == ')') {
        return;
      }
      
      if (typ2 != typ) {
        var err = 'Očakávame spojku "' + (typ == 'OR'? 'alebo' : 'a') + '"';
        if (typ2 == 'OR' || typ2 == 'AND') {
          errors.add(tokens.idx(), err);
          tokens.getOne();
        }
        else {
          errors.addBefore(tokens.idx(), err);
        }
      }
      else {
        tokens.getOne();
      }
    }
  }
  
  window.validateSubjCond = function(text) {
    var tok = new TokenStream(text);
    var errors = new Errors();
    if (tok.peek() !== null) {
      parse_expr_in(tok, errors);
    }
    return errors.getAll();
  }
})();