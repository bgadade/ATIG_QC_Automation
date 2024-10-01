var app = angular.module('myapp', ['ui.router','ngFileUpload','ui.select']);

app.config(function($stateProvider, $urlRouterProvider) {

  $urlRouterProvider.otherwise('/login');

  $stateProvider.state('login',{
    url:'/login',
    views:{
      "content":{
        templateUrl: "static/template/login_alt.html",
        controller: "LoginController"
      }
    }
  })
  .state('error',{
  url:'/error',
  views:{
    "header":{
      templateUrl: "static/template/mainHeader.html",
      controller: "HeaderController"
    },
    "content":{
      templateUrl: "static/template/error.html"
    },
    "footer":{
      templateUrl: "static/template/mainFooter.html"
    }
  }
})
  .state('home',{
    url:'/home',
    views:{
      "header":{
        templateUrl: "static/template/mainHeader.html",
        controller: "HeaderController"
      },
      "content":{
        templateUrl: "static/template/input.html",
        controller: "InputController"
      },
      "footer":{
        templateUrl: "static/template/mainFooter.html"
      }
    }
  })

  .state('mngUsr',{
    url:'/manageUser',
    views:{
      "header":{
        templateUrl: "static/template/mainHeader.html",
        controller: "HeaderController"
      },
      "content":{
        templateUrl: "static/template/manageUsrs.html",
        controller: "MngUsrController"
      },
      "footer":{
        templateUrl: "static/template/mainFooter.html"
      }
    }
  })
   .state('uploadExcel',{
    url:'/uploadExcel',
    views:{
      "header":{
        templateUrl: "static/template/mainHeader.html",
        controller: "HeaderController"
      },
      "content":{
        templateUrl: "static/template/uploadExcelFile.html",
        controller: "uploadExcelController"
      },
      "footer":{
        templateUrl: "static/template/mainFooter.html"
      }
    }
  })
  .state('uploadPDF',{
   url:'/uploadPDF',
   views:{
     "header":{
       templateUrl: "static/template/mainHeader.html",
       controller: "HeaderController"
     },
     "content":{
       templateUrl: "static/template/processPdfFiles.html",
       controller: "InputController"
     },
     "footer":{
       templateUrl: "static/template/mainFooter.html"
     }
   }
 })
  .state('newUser',{
    url:'/addNewUser',
    views:{
      "header":{
        templateUrl: "static/template/mainHeader.html",
        controller: "HeaderController"
      },
      "content":{
        templateUrl: "static/template/addNewUser.html",
        controller: "MngUsrController"
      },
      "footer":{
        templateUrl: "static/template/mainFooter.html"
      }
    }
  });
});
